def classify_output(waste_type, residue_score):
    """Classify waste based on type and residue score"""
    # Initialize scores
    waste_type_score = 0
    cleanliness_score = 0
    
    # Score based on waste type
    if waste_type == 'PET Bottle':
        waste_type_score = 10
    elif waste_type == 'HDPE Plastic':
        waste_type_score = 9
    elif waste_type == 'LDPE':
        waste_type_score = 7
    elif waste_type == 'PP':
        waste_type_score = 8
    elif waste_type == 'Tin-Steel Can':
        waste_type_score = 9
    elif waste_type == 'UHT Box':
        # UHT boxes are automatically classified as Mixed
        return 'Mixed'
    else:
        waste_type_score = 5
    
    # Score based on cleanliness (residue score)
    if residue_score < 5:
        cleanliness_score = 10
    elif residue_score < 10:
        cleanliness_score = 8
    elif residue_score < 15:
        cleanliness_score = 6
    elif residue_score < 20:
        cleanliness_score = 4
    elif residue_score < 25:
        cleanliness_score = 2
    else:
        cleanliness_score = 0
    
    # Calculate final score
    final_score = (waste_type_score * 0.6) + (cleanliness_score * 0.4)
    
    # Print classification breakdown
    print("\nClassification Breakdown:")
    print(f"  - Waste Type: '{waste_type}' → Score: {waste_type_score} × 0.6 = {waste_type_score * 0.6:.2f}")
    print(f"  - Residue Score: {residue_score} → Cleanliness Score: {cleanliness_score} × 0.4 = {cleanliness_score * 0.4:.2f}")
    print(f"  → Final Score: {final_score:.2f}")

    # Determine classification based on final score and waste type
    if waste_type == 'PET Bottle':
        if residue_score > 10:  # New threshold for PET
            classification = 'Low Value'
        else:
            classification = 'High Value'
    elif waste_type == 'HDPE Plastic':
        if residue_score > 15:  # New threshold for HDPE
            classification = 'Low Value'
        else:
            classification = 'High Value'
    elif waste_type == 'Tin-Steel Can':
        classification = 'High Value' if residue_score < 25 else 'Low Value'
    else:
        classification = 'High Value' if final_score >= 7.0 else 'Low Value'

    return classification 