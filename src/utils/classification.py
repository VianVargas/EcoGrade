def classify_output(waste_type, residue_score):
    """Classify waste based on type and residue score"""
    # Return Mixed for unknown waste types
    if waste_type == 'Unknown':
        return 'Mixed'
        
    waste_type_score = 0
    cleanliness_score = 0

    # Waste type scoring
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
        return 'Mixed'  # Automatically classified
    else:
        waste_type_score = 5

    # Cleanliness scoring
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

    # Weighted score
    final_score = (waste_type_score * 0.6) + (cleanliness_score * 0.4)

    print("\nClassification Breakdown:")
    print(f"  - Waste Type: '{waste_type}' → Score: {waste_type_score} × 0.6 = {waste_type_score * 0.6:.2f}")
    print(f"  - Residue Score: {residue_score} → Cleanliness Score: {cleanliness_score} × 0.4 = {cleanliness_score * 0.4:.2f}")
    print(f"  → Final Score (pre-bonus): {final_score:.2f}")

    # Classification logic
    if waste_type == 'PET Bottle' or waste_type == 'HDPE Plastic':
        if residue_score <= 5:
            classification = 'High Value'
            final_score *= 1.05
        elif residue_score <= 15:
            classification = 'Low Value'
            final_score *= 1.15  # avg boost
        else:
            classification = 'Rejected'
    elif waste_type in ['LDPE', 'PP']:
        if residue_score <= 15:
            classification = 'Low Value'
            final_score *= 1.15
        else:
            classification = 'Rejected'
    elif waste_type == 'Tin-Steel Can':
        if residue_score <= 25:
            classification = 'High Value'
            final_score *= 1.05
        else:
            classification = 'Low Value'
            final_score *= 1.15
    else:
        if final_score >= 7.0:
            classification = 'High Value'
            final_score *= 1.05
        else:
            classification = 'Low Value'
            final_score *= 1.15

    print(f"  → Final Score (after bonus): {final_score:.2f}")
    print(f"  → Classification: {classification}")
    return classification