#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from ultralytics import YOLO
import onnx
import onnxruntime as ort
import numpy as np

def convert_to_onnx(model_path, output_dir, opset=12, simplify=True, optimize=True):
    """
    Convert YOLO model to ONNX format with optimizations for edge devices.
    
    Args:
        model_path (str): Path to the YOLO model (.pt file)
        output_dir (str): Directory to save the ONNX model
        opset (int): ONNX operator set version
        simplify (bool): Whether to simplify the ONNX model
        optimize (bool): Whether to optimize the ONNX model
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load YOLO model
        print(f"Loading YOLO model from {model_path}...")
        model = YOLO(model_path)
        
        # Export to ONNX format
        print("Converting to ONNX format...")
        onnx_path = os.path.join(output_dir, "best.onnx")
        model.export(format='onnx', opset=opset, simplify=simplify)
        
        # Move the exported model to the output directory
        exported_path = str(Path(model_path).with_suffix('.onnx'))
        if os.path.exists(exported_path):
            os.rename(exported_path, onnx_path)
        
        # Verify ONNX model
        print("Verifying ONNX model...")
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        
        # Optimize ONNX model
        if optimize:
            print("Optimizing ONNX model for edge devices...")
            # Create ONNX Runtime session options
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.intra_op_num_threads = 4  # Optimize for Raspberry Pi 5's 4 cores
            
            # Create optimized model
            optimized_model = ort.InferenceSession(onnx_path, session_options)
            
            # Save optimized model using ONNX save
            optimized_path = os.path.join(output_dir, "best_optimized.onnx")
            onnx.save(onnx_model, optimized_path)
            
            # Verify optimized model
            onnx_model = onnx.load(optimized_path)
            onnx.checker.check_model(onnx_model)
            
            print(f"Optimized model saved to {optimized_path}")
        
        print(f"Conversion completed successfully!")
        print(f"Original ONNX model saved to {onnx_path}")
        
        # Print model information
        print("\nModel Information:")
        print(f"Input shape: {onnx_model.graph.input[0].type.tensor_type.shape}")
        print(f"Output shape: {onnx_model.graph.output[0].type.tensor_type.shape}")
        print(f"Number of nodes: {len(onnx_model.graph.node)}")
        
        return True
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert YOLO model to ONNX format with optimizations')
    parser.add_argument('--model', type=str, required=True, help='Path to YOLO model (.pt file)')
    parser.add_argument('--output', type=str, default='models', help='Output directory for ONNX model')
    parser.add_argument('--opset', type=int, default=12, help='ONNX operator set version')
    parser.add_argument('--no-simplify', action='store_true', help='Disable model simplification')
    parser.add_argument('--no-optimize', action='store_true', help='Disable model optimization')
    
    args = parser.parse_args()
    
    success = convert_to_onnx(
        args.model,
        args.output,
        opset=args.opset,
        simplify=not args.no_simplify,
        optimize=not args.no_optimize
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 