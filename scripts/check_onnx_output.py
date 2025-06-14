#!/usr/bin/env python3
import onnxruntime as ort
import numpy as np
import cv2

def check_onnx_output(model_path='models/best_optimized.onnx'):
    # Create ONNX Runtime session
    session = ort.InferenceSession(model_path)
    
    # Get model metadata
    input_name = session.get_inputs()[0].name
    output_names = [output.name for output in session.get_outputs()]
    
    print("\nModel Information:")
    print(f"Input name: {input_name}")
    print(f"Output names: {output_names}")
    
    # Print input and output shapes
    for input_info in session.get_inputs():
        print(f"\nInput shape: {input_info.shape}")
    
    for output_info in session.get_outputs():
        print(f"Output shape: {output_info.shape}")
    
    # Create a dummy input
    dummy_input = np.random.randn(1, 3, 640, 640).astype(np.float32)
    
    # Run inference
    outputs = session.run(output_names, {input_name: dummy_input})
    
    print("\nOutput Information:")
    for i, output in enumerate(outputs):
        print(f"\nOutput {i}:")
        print(f"Shape: {output.shape}")
        print(f"Type: {output.dtype}")
        print(f"Sample values: {output[0, :5]}")  # Print first 5 values

if __name__ == '__main__':
    check_onnx_output() 