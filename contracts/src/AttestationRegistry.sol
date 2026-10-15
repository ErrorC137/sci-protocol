// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title AttestationRegistry
/// @notice Two deliberately separate record types:
///   1. anchor()  - anyone timestamps a hash they possess (e.g. keccak256 of an encrypted vault
///                  blob). A timestamped existence proof - NOT prior art, NOT a patent filing,
///                  NOT legal IP registration.
///   2. attest()  - a role-gated attestor records a verification claim about a project
///                  (milestone evidence reviewed, TRL confirmed). The attestor set is
///                  centralized in this demo; decentralizing it is future work.
contract AttestationRegistry is AccessControl {
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");

    struct Anchor {
        address submitter;
        uint64 timestamp;
        string cid;
    }

    struct Attestation {
        uint256 projectId;
        bytes32 claimHash;
        address attestor;
        uint64 timestamp;
        string evidenceCID;
    }

    mapping(bytes32 => Anchor) private _anchors;
    Attestation[] private _attestations;
    mapping(uint256 => uint256[]) private _projectAttestations;

    event Anchored(bytes32 indexed hash, address indexed submitter, string cid, uint64 timestamp);
    event Attested(
        uint256 indexed projectId, bytes32 indexed claimHash, address indexed attestor, string evidenceCID, uint256 index
    );

    error AlreadyAnchored(bytes32 hash, address submitter, uint64 timestamp);
    error ZeroHash();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice First anchor of a hash wins; later attempts revert so the original timestamp stands.
    function anchor(bytes32 hash, string calldata cid) external {
        if (hash == bytes32(0)) revert ZeroHash();
        Anchor storage a = _anchors[hash];
        if (a.submitter != address(0)) revert AlreadyAnchored(hash, a.submitter, a.timestamp);
        _anchors[hash] = Anchor({submitter: msg.sender, timestamp: uint64(block.timestamp), cid: cid});
        emit Anchored(hash, msg.sender, cid, uint64(block.timestamp));
    }

    function attest(uint256 projectId, bytes32 claimHash, string calldata evidenceCID)
        external
        onlyRole(ATTESTOR_ROLE)
        returns (uint256 index)
    {
        if (claimHash == bytes32(0)) revert ZeroHash();
        index = _attestations.length;
        _attestations.push(
            Attestation({
                projectId: projectId,
                claimHash: claimHash,
                attestor: msg.sender,
                timestamp: uint64(block.timestamp),
                evidenceCID: evidenceCID
            })
        );
        _projectAttestations[projectId].push(index);
        emit Attested(projectId, claimHash, msg.sender, evidenceCID, index);
    }

    function getAnchor(bytes32 hash) external view returns (Anchor memory) {
        return _anchors[hash];
    }

    function attestationCount() external view returns (uint256) {
        return _attestations.length;
    }

    function getAttestation(uint256 index) external view returns (Attestation memory) {
        return _attestations[index];
    }

    function attestationsOf(uint256 projectId) external view returns (Attestation[] memory out) {
        uint256[] storage idx = _projectAttestations[projectId];
        out = new Attestation[](idx.length);
        for (uint256 i; i < idx.length; ++i) out[i] = _attestations[idx[i]];
    }
}
