"""
Concrete implementation of the ModelInterface for models loaded locally.
"""
from typing import Dict, Any, List, Union, Optional
import joblib # For scikit-learn model loading, can be adapted
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, log_loss, classification_report
from sklearn.exceptions import NotFittedError
import os # For example usage file cleanup

from .interfaces import ModelInterface, DatasetType, FilePathType
from envirosense.utils.avro_io import load_avro_data # Ensure this path is correct

# Placeholder for actual MLDataSample structure if needed for preprocessing
# from ..schemas.avro_generated import MLDataSample # Or similar

class LocalModelInterface(ModelInterface):
    """
    ModelInterface implementation for ML models that can be loaded
    directly from a local file path (e.g., scikit-learn pickled models).
    """

    def __init__(self, model_path: str):
        """
        Initializes the LocalModelInterface.

        Args:
            model_path: Path to the serialized model file.
        """
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        """Loads the model from the specified path."""
        try:
            # Example for scikit-learn, adapt for other model types
            self.model = joblib.load(self.model_path)
            print(f"Model loaded successfully from {self.model_path}")
        except FileNotFoundError:
            print(f"Error: Model file not found at {self.model_path}")
            raise
        except Exception as e:
            print(f"Error loading model from {self.model_path}: {e}")
            raise

    def _preprocess_data(self, dataset: DatasetType) -> Any:
        """
        Placeholder for preprocessing data into the format expected by the model.
        This will be highly dependent on the specific model.
        
        Args:
            dataset: List of MLDataSample-like dictionaries.

        Returns:
            Processed data ready for model prediction.
        """
        # Example: Extracting a feature vector. This is highly model-specific.
        # Assume each sample in dataset is a dict and we need to extract 'features'
        # which is a list/array of numerical values.
        # This needs to be adapted based on actual MLDataSample structure and model needs.
        
        # This is a generic placeholder. Real preprocessing is highly model-specific.
        # It attempts to extract numerical features from sensor_readings_map.
        # The number of features can vary per sample if not careful.
        # For a more robust generic approach, one might define a fixed feature set
        # or use techniques like feature hashing if the raw feature space is too diverse.

        all_features_list = []
        max_len = 0 # To pad to a consistent length if needed by the model

        for i, sample in enumerate(dataset):
            features = []
            srm = sample.get("sensor_readings_map", {})
            if isinstance(srm, dict):
                for sensor_id, reading_data_union in sorted(srm.items()): # Sort for consistency
                    if reading_data_union and isinstance(reading_data_union, dict):
                        # The reading_data_union is a dict like {"com.example.ThermalReading": {...}}
                        # Get the actual reading data dict
                        actual_reading_data_values = list(reading_data_union.values())
                        if actual_reading_data_values and isinstance(actual_reading_data_values[0], dict):
                            actual_reading_data = actual_reading_data_values[0]
                            for _, val in sorted(actual_reading_data.items()): # Sort for consistency
                                if isinstance(val, (int, float)):
                                    features.append(float(val))
                                elif isinstance(val, list) and all(isinstance(item, (int, float)) for item in val):
                                    features.extend(float(item) for item in val)
                                # Add more type handling if necessary (e.g., booleans to 0/1)
            
            if not features:
                # If no features extracted, use a default vector (e.g., all zeros)
                # The length of this default vector should ideally be known or determined.
                # For now, let's use a small default if others also yield no features.
                # This part is tricky without knowing the model's expected input dimension.
                print(f"Warning: No numerical features extracted for sample {sample.get('ml_data_sample_id', i)}. Using [0.0].")
                features = [0.0]
            
            all_features_list.append(features)
            if len(features) > max_len:
                max_len = len(features)

        # Pad features to ensure all samples have the same number of features
        # This is a common requirement for many scikit-learn models.
        # Padding with zero, other strategies might be better (e.g., mean).
        padded_features_list = []
        if max_len == 0 and all_features_list: # All samples yielded no features
             print(f"Warning: All {len(all_features_list)} samples yielded no features. Using a default feature vector of [0.0] for all.")
             padded_features_list = [[0.0]] * len(all_features_list)
        elif max_len > 0 :
            for features in all_features_list:
                padded_features = features + [0.0] * (max_len - len(features))
                padded_features_list.append(padded_features)
        
        if not padded_features_list and dataset: # If dataset was not empty but processing failed
             print(f"Warning: Preprocessing resulted in an empty feature set for {len(dataset)} samples. Using default features.")
             # This indicates a more fundamental issue with feature extraction logic or data.
             # Provide a default shape that a dummy model might expect, e.g., (num_samples, 1)
             return np.zeros((len(dataset), 1))


        return np.array(padded_features_list)


    def get_model_performance_feedback(
        self,
        evaluation_dataset: Union[DatasetType, FilePathType],
        model_version_tag: Optional[str] = None # Not used by this local loader, model path is fixed
    ) -> Dict[str, Any]:
        """
        Evaluates the loaded model on the provided dataset and returns structured feedback.
        """
        if self.model is None:
            print("Error: Model is not loaded.")
            try:
                self._load_model()
                if self.model is None:
                     raise ValueError("Model could not be re-loaded for evaluation.")
            except Exception as e:
                 raise ValueError(f"Model could not be re-loaded for evaluation: {e}")

        if isinstance(evaluation_dataset, FilePathType):
            dataset_list = load_avro_data(evaluation_dataset)
            if not dataset_list:
                print(f"Warning: No data loaded from {evaluation_dataset}. Returning empty feedback.")
                return {"error": f"No data loaded from {evaluation_dataset}"}
        else:
            dataset_list = evaluation_dataset

        if not dataset_list:
            print("Warning: Evaluation dataset is empty. Returning empty feedback.")
            return {"error": "Evaluation dataset is empty"}

        try:
            X_eval = self._preprocess_data(dataset_list)
            if X_eval.size == 0 and dataset_list: # Preprocessing failed to produce features
                 print("Error: Feature preprocessing resulted in an empty dataset. Cannot evaluate.")
                 return {"error": "Feature preprocessing failed for all samples."}
            if X_eval.size == 0 and not dataset_list: # Should have been caught earlier
                 return {"error": "Evaluation dataset is effectively empty after preprocessing."}


            y_true_labels_str = [str(sample.get('ground_truth_labels', {}).get('event_type', 'unknown_class')) for sample in dataset_list]
            
            predictions_str = [str(p) for p in self.model.predict(X_eval)]
            probabilities = None
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba(X_eval)
        
        except NotFittedError as nfe:
            print(f"Error: Model at {self.model_path} is not fitted. {nfe}")
            return {"error": f"Model not fitted: {nfe}", "overall_metrics": {}, "per_class_metrics": {}, "uncertain_samples": [], "misclassified_samples": []}
        except Exception as e:
            print(f"Error during model prediction or data processing: {e}")
            return {"error": str(e), "overall_metrics": {}, "per_class_metrics": {}, "uncertain_samples": [], "misclassified_samples": []}

        # Calculate metrics
        unique_labels = sorted(list(set(y_true_labels_str + predictions_str)))
        
        overall_metrics = {
            "accuracy": accuracy_score(y_true_labels_str, predictions_str),
            "f1_macro": f1_score(y_true_labels_str, predictions_str, average='macro', zero_division=0),
            # "f1_weighted": f1_score(y_true_labels_str, predictions_str, average='weighted', zero_division=0),
        }
        if probabilities is not None and len(unique_labels) > 1 : # log_loss requires at least 2 classes
            try:
                # Ensure labels used for log_loss are known to the model if it's strict
                # This might require mapping string labels to integer indices if model expects that
                # For scikit-learn, if classes_ attribute exists, it can be used.
                model_classes = getattr(self.model, 'classes_', unique_labels)
                ll = log_loss(y_true_labels_str, probabilities, labels=model_classes)
                overall_metrics["log_loss"] = ll
            except ValueError as lve:
                 print(f"Warning: Could not calculate log_loss: {lve}. Probabilities shape: {probabilities.shape}, y_true shape: {len(y_true_labels_str)}, model_classes: {model_classes}")
                 overall_metrics["log_loss"] = None # Or some indicator like -1
            except Exception as e_ll:
                 print(f"Unexpected error calculating log_loss: {e_ll}")
                 overall_metrics["log_loss"] = None


        per_class_metrics_report = classification_report(y_true_labels_str, predictions_str, output_dict=True, zero_division=0, labels=unique_labels)
        per_class_metrics = {
            label: data for label, data in per_class_metrics_report.items() if label not in ['accuracy', 'macro avg', 'weighted avg']
        }

        feedback: Dict[str, Any] = {
            "model_version_evaluated": model_version_tag or self.model_path,
            "dataset_source_identifier": str(evaluation_dataset) if isinstance(evaluation_dataset, FilePathType) else f"in_memory_dataset_len_{len(dataset_list)}",
            "overall_metrics": overall_metrics,
            "per_class_metrics": per_class_metrics,
            "uncertain_samples": [],
            "misclassified_samples": []
        }

        # Populate uncertain_samples and misclassified_samples
        for i, sample in enumerate(dataset_list):
            sample_id = sample.get('ml_data_sample_id', f"sample_{i}")
            true_label = y_true_labels_str[i]
            predicted_label = predictions_str[i]
            
            # Placeholder for actual feature summary (raw features from X_eval for now)
            # True feature importance (SHAP, LIME) is model-specific and complex.
            raw_features_for_sample = X_eval[i].tolist() if i < len(X_eval) else []
            sample_features_summary = {
                 "raw_features": raw_features_for_sample, # Basic, not "importance"
                 "top_n_features": [{"feature_path": f"feature_{j}", "raw_value": val, "importance_score": None} for j, val in enumerate(raw_features_for_sample[:5])] # Top 5 raw
            }


            # Misclassified samples
            if predicted_label != true_label and true_label != 'unknown_class':
                misclassified_sample_info = {
                    "sample_id": sample_id,
                    "true_label": true_label,
                    "predicted_label": predicted_label,
                    "sample_features_summary": sample_features_summary
                }
                if probabilities is not None and i < len(probabilities):
                    # Find index of predicted_label in model's classes to get probability
                    try:
                        pred_label_idx = list(self.model.classes_).index(predicted_label)
                        misclassified_sample_info["prediction_probability"] = float(probabilities[i][pred_label_idx])
                    except (ValueError, AttributeError, IndexError):
                         misclassified_sample_info["prediction_probability"] = None # Or max prob if classes don't match
                feedback["misclassified_samples"].append(misclassified_sample_info)

            # Uncertain samples (using least confidence if probabilities are available)
            if probabilities is not None and i < len(probabilities):
                max_prob = float(np.max(probabilities[i]))
                confidence = max_prob
                epistemic_uncertainty = 1.0 - confidence # Simple least confidence

                # Define a threshold or take top N uncertain
                uncertainty_threshold = 0.3 # Example: if 1 - max_prob > 0.3 (i.e. max_prob < 0.7)
                if epistemic_uncertainty > uncertainty_threshold:
                    feedback["uncertain_samples"].append({
                        "sample_id": sample_id,
                        "true_label": true_label,
                        "predicted_label": predicted_label,
                        "uncertainty_scores": {
                            "epistemic_uncertainty_score": epistemic_uncertainty,
                            "confidence_score": confidence
                        },
                        "sample_features_summary": sample_features_summary
                    })
        
        # If too many uncertain samples, cap them (e.g., top 10 by uncertainty)
        if feedback["uncertain_samples"]:
            feedback["uncertain_samples"] = sorted(feedback["uncertain_samples"], key=lambda x: x["uncertainty_scores"]["epistemic_uncertainty_score"], reverse=True)[:10]


        print(f"Generated performance feedback for model {self.model_path}.")
        return feedback

if __name__ == '__main__':
    # Example Usage (requires a dummy model and dummy Avro data)
    print("LocalModelInterface module loaded. Example usage:")

    # 1. Create a dummy scikit-learn model and save it
    from sklearn.linear_model import LogisticRegression
    import datetime # For Avro example
    import fastavro # For Avro example
    import json # For pretty printing

    dummy_model_file = "dummy_model.joblib"
    dummy_avro_eval_file = "dummy_eval_data.avro"
    # Define a simple Avro schema for MLDataSample for the example
    # This should ideally match your project's MLDataSample.avsc
    dummy_mldatasample_schema_def = {
        "type": "record", "name": "MLDataSample", "namespace": "com.envirosense.dummy",
        "fields": [
            {"name": "ml_data_sample_id", "type": "string"},
            {"name": "sensor_readings_map", "type": {
                "type": "map",
                "values": { # Union of possible reading types
                    "type": "map", "values": ["null", "double", "string", {"type": "array", "items": "double"}]
                }
            }}, # Simplified: map of sensor_id to map of feature_name to value
            {"name": "ground_truth_labels", "type": {"type": "map", "values": ["null", "string", "double", "boolean"]}}
        ]
    }
    parsed_mldatasample_schema = fastavro.parse_schema(dummy_mldatasample_schema_def)


    try:
        # 1. Create and save a dummy scikit-learn model
        # Consistent number of features for the dummy model
        num_features = 5
        X_train_dummy = np.random.rand(100, num_features)
        y_train_dummy_classes = ["class_A", "class_B", "class_C"]
        y_train_dummy = np.random.choice(y_train_dummy_classes, 100)
        
        dummy_model = LogisticRegression(solver='liblinear') # liblinear is often robust for small datasets
        dummy_model.fit(X_train_dummy, y_train_dummy)
        joblib.dump(dummy_model, dummy_model_file)
        print(f"Dummy model saved to {dummy_model_file}")

        # 2. Create dummy evaluation data (list of dicts)
        dummy_eval_dataset_list: DatasetType = []
        for i in range(20): # More samples for better metric demo
            # Generate features that _preprocess_data can handle
            # This needs to align with how _preprocess_data extracts features
            # For this example, let's make sensor_readings_map simpler
            readings = {}
            for f_idx in range(num_features):
                 # Create a structure that _preprocess_data can parse into flat features
                 # Example: sensor_readings_map: {"sensor1": {"feature_value_wrapper": {"feature_0": 0.5, "feature_1": 0.3}}}
                 # The current _preprocess_data flattens all numeric values it finds.
                 # Let's make it simpler:
                 readings[f"dummy_sensor_{f_idx}"] = { "com.example.ValueReading": {f"value": np.random.rand()}}

            dummy_eval_dataset_list.append({
                "ml_data_sample_id": f"eval_sample_{i}",
                "sensor_readings_map": readings,
                "ground_truth_labels": {"event_type": np.random.choice(y_train_dummy_classes)}
            })
        
        # 3. Initialize and use LocalModelInterface with in-memory data
        model_interface = LocalModelInterface(model_path=dummy_model_file)
        
        print("\nEvaluating with in-memory dataset:")
        feedback_list = model_interface.get_model_performance_feedback(dummy_eval_dataset_list)
        
        if feedback_list.get("error"):
            print(f"Error during evaluation: {feedback_list['error']}")
        else:
            print("Feedback from in-memory dataset (first 2 uncertain, 2 misclassified):")
            print(f"  Overall Accuracy: {feedback_list.get('overall_metrics', {}).get('accuracy')}")
            print(f"  Overall F1 Macro: {feedback_list.get('overall_metrics', {}).get('f1_macro')}")
            print(f"  Overall Log Loss: {feedback_list.get('overall_metrics', {}).get('log_loss')}")
            print("  Per-class metrics (first class):")
            first_class_key = list(feedback_list.get('per_class_metrics', {}).keys())[0] if feedback_list.get('per_class_metrics') else None
            if first_class_key:
                 print(f"    {first_class_key}: {feedback_list['per_class_metrics'][first_class_key]}")

            print(f"  Number of uncertain samples reported (capped at 10): {len(feedback_list.get('uncertain_samples', []))}")
            if feedback_list.get('uncertain_samples'):
                for us_idx, us in enumerate(feedback_list['uncertain_samples'][:2]):
                    print(f"    Uncertain Sample {us_idx+1} ID: {us['sample_id']}, True: {us['true_label']}, Pred: {us['predicted_label']}, UncertScore: {us['uncertainty_scores']['epistemic_uncertainty_score']:.2f}")
            
            print(f"  Number of misclassified samples: {len(feedback_list.get('misclassified_samples', []))}")
            if feedback_list.get('misclassified_samples'):
                for mc_idx, mc in enumerate(feedback_list['misclassified_samples'][:2]):
                     print(f"    Misclassified Sample {mc_idx+1} ID: {mc['sample_id']}, True: {mc['true_label']}, Pred: {mc['predicted_label']}")


        # 4. Test with an Avro file
        try:
            with open(dummy_avro_eval_file, "wb") as fo:
                fastavro.writer(fo, parsed_mldatasample_schema, dummy_eval_dataset_list)
            print(f"\nDummy Avro evaluation data written to {dummy_avro_eval_file}")

            print("\nEvaluating with Avro file dataset:")
            feedback_avro = model_interface.get_model_performance_feedback(dummy_avro_eval_file)
            if feedback_avro.get("error"):
                 print(f"Error during Avro evaluation: {feedback_avro['error']}")
            else:
                print("Feedback from Avro file:")
                print(f"  Overall Accuracy: {feedback_avro.get('overall_metrics', {}).get('accuracy')}")
        except Exception as e_avro:
            print(f"Error during Avro file test: {e_avro}")


    except Exception as e:
        print(f"An error occurred in example usage: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up dummy files
        if os.path.exists(dummy_model_file):
            os.remove(dummy_model_file)
        if os.path.exists(dummy_avro_eval_file):
            os.remove(dummy_avro_eval_file)
        print("Example usage finished.")