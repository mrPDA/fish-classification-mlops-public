#!/usr/bin/env python3
"""
🐟 Script to register existing MLflow model to Model Registry
"""

import mlflow
from mlflow.tracking import MlflowClient
import sys

# Configuration
MLFLOW_URI = "http://51.250.15.131:5000"
RUN_ID = "bcef140c268343d18847ec0f83245f34"
MODEL_NAME = "fish-classifier-efficientnet-b4"
MODEL_PATH = "model"  # artifact path in the run

def main():
    print("🐟 Fish Classification - Model Registration")
    print("=" * 60)
    
    # Set tracking URI
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = MlflowClient()
    
    print(f"\n📊 Configuration:")
    print(f"  MLflow URI: {MLFLOW_URI}")
    print(f"  Run ID: {RUN_ID}")
    print(f"  Model Name: {MODEL_NAME}")
    
    # Check if run exists
    print(f"\n🔍 Checking run...")
    try:
        run = client.get_run(RUN_ID)
        print(f"  ✅ Run found: {run.info.status}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)
    
    # Check if model already registered
    print(f"\n🔍 Checking if model already registered...")
    try:
        registered_models = client.search_registered_models(f"name='{MODEL_NAME}'")
        if registered_models:
            print(f"  ⚠️  Model '{MODEL_NAME}' already exists")
            model = registered_models[0]
            latest_version = model.latest_versions[0] if model.latest_versions else None
            if latest_version:
                print(f"  Current version: {latest_version.version}")
                print(f"  Stage: {latest_version.current_stage}")
        else:
            print(f"  ℹ️  Model not registered yet")
    except Exception as e:
        print(f"  ℹ️  Model doesn't exist: {e}")
    
    # Register model
    print(f"\n📦 Registering model...")
    try:
        model_uri = f"runs:/{RUN_ID}/{MODEL_PATH}"
        print(f"  Model URI: {model_uri}")
        
        result = mlflow.register_model(
            model_uri=model_uri,
            name=MODEL_NAME
        )
        
        print(f"  ✅ Model registered successfully!")
        print(f"  Name: {result.name}")
        print(f"  Version: {result.version}")
        
    except Exception as e:
        print(f"  ❌ Registration failed: {e}")
        sys.exit(1)
    
    # Transition to Production
    print(f"\n🚀 Transitioning to Production stage...")
    try:
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=result.version,
            stage="Production",
            archive_existing_versions=True  # Archive old production versions
        )
        print(f"  ✅ Model transitioned to Production!")
        
    except Exception as e:
        print(f"  ❌ Transition failed: {e}")
        print(f"  You can transition manually via UI")
        sys.exit(1)
    
    # Verify
    print(f"\n✅ Verification:")
    try:
        # Get production model
        prod_model = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if prod_model:
            print(f"  ✅ Production model found!")
            print(f"  Version: {prod_model[0].version}")
            print(f"  Run ID: {prod_model[0].run_id}")
            print(f"  Stage: {prod_model[0].current_stage}")
        else:
            print(f"  ⚠️  No production model found")
    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Model registration complete!")
    print("\nNext steps:")
    print("  1. Check MLflow UI: http://51.250.15.131:5000/#/models")
    print(f"  2. View model: http://51.250.15.131:5000/#/models/{MODEL_NAME}")
    print("  3. Deploy inference: ./scripts/deploy_full_stack.sh")
    print()

if __name__ == "__main__":
    main()

