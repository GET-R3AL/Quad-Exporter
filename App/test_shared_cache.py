#!/usr/bin/env python3
"""
Test script to verify the new SharedCache functionality
"""
import os
import sys

# Test the new path detection logic
def test_shared_cache_detection():
    print("Testing SharedCache path detection...")
    
    # Test paths
    test_cases = [
        (r"C:\Program Files\EVE\SharedCache\ResFiles", r"C:\Program Files\EVE\SharedCache"),
        (r"C:\EVE\SharedCache\ResFiles", r"C:\EVE\SharedCache"),
        (r"D:\Games\EVE\SharedCache\ResFiles", r"D:\Games\EVE\SharedCache"),
    ]
    
    for resfiles_path, expected_shared_cache in test_cases:
        # Simulate the getSharedCacheFromResPath logic
        if "SharedCache" in resfiles_path:
            sharedCacheIndex = resfiles_path.find("SharedCache")
            if sharedCacheIndex != -1:
                result = resfiles_path[:sharedCacheIndex + len("SharedCache")]
            else:
                result = ""
        else:
            result = ""
        
        print(f"ResFiles: {resfiles_path}")
        print(f"Expected: {expected_shared_cache}")
        print(f"Got:      {result}")
        print(f"Match:    {result == expected_shared_cache}")
        print()

def test_server_detection():
    print("Testing server detection from index paths...")
    
    test_cases = [
        (r"C:\Program Files\EVE\SharedCache\tq\resfileindex.txt", "tq"),
        (r"C:\EVE\SharedCache\sisi\resfileindex.txt", "sisi"),
        (r"D:\Games\EVE\SharedCache\thunderdome\resfileindex.txt", "thunderdome"),
    ]
    
    for index_path, expected_server in test_cases:
        # Simulate the getServerFromIndexPath logic
        if "\\tq\\" in index_path or "/tq/" in index_path:
            result = "tq"
        elif "\\sisi\\" in index_path or "/sisi/" in index_path:
            result = "sisi"
        elif "\\thunderdome\\" in index_path or "/thunderdome/" in index_path:
            result = "thunderdome"
        else:
            result = "tq"  # Default
        
        print(f"Index path: {index_path}")
        print(f"Expected:   {expected_server}")
        print(f"Got:        {result}")
        print(f"Match:      {result == expected_server}")
        print()

def test_path_construction():
    print("Testing path construction from SharedCache + server...")
    
    shared_cache = r"C:\Program Files\EVE\SharedCache"
    servers = ["tq", "sisi", "thunderdome"]
    
    for server in servers:
        resfiles_path = os.path.join(shared_cache, "ResFiles")
        index_path = os.path.join(shared_cache, server, "resfileindex.txt")
        
        print(f"Server: {server}")
        print(f"ResFiles: {resfiles_path}")
        print(f"Index:    {index_path}")
        print()

if __name__ == "__main__":
    test_shared_cache_detection()
    test_server_detection()
    test_path_construction()
    print("All tests completed!")