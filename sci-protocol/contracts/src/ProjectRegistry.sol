// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ProjectRegistry
/// @notice Canonical on-chain record of a research project. Stores only non-confidential
///         metadata (an IPFS CID) and, optionally, the hash of a client-side-encrypted
///         private detail blob. Never stores anything that could affect patentability.
contract ProjectRegistry is AccessControl {
    /// @notice May update a project's TRL after reviewing evidence. Centralized in the demo.
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");
    /// @notice Granted to FundingPool and MilestoneEscrow so they can move a project through its lifecycle.
    bytes32 public constant MODULE_ROLE = keccak256("MODULE_ROLE");

    enum Status {
        Draft,
        Open,
        Funded,
        Completed,
        Failed
    }

    struct Project {
        address researcher;
        string metadataCID;
        bytes32 privateDetailHash;
        uint8 trl;
        Status status;
        uint64 createdAt;
    }

    /// @notice Number of registered projects. Project ids start at 1, so 0 always means "none".
    uint256 public projectCount;
    mapping(uint256 => Project) private _projects;

    event ProjectRegistered(uint256 indexed projectId, address indexed researcher, string metadataCID, uint8 trl);
    event MetadataUpdated(uint256 indexed projectId, string metadataCID);
    event PrivateDetailHashSet(uint256 indexed projectId, bytes32 privateDetailHash);
    event TRLUpdated(uint256 indexed projectId, uint8 oldTRL, uint8 newTRL, address indexed attestor);
    event StatusChanged(uint256 indexed projectId, Status status);

    error InvalidTRL(uint8 trl);
    error EmptyCID();
    error UnknownProject(uint256 projectId);
    error NotResearcher(uint256 projectId, address caller);
    error NotDraft(uint256 projectId);

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    modifier onlyResearcher(uint256 projectId) {
        if (_projects[projectId].researcher != msg.sender) revert NotResearcher(projectId, msg.sender);
        _;
    }

    function registerProject(string calldata metadataCID, uint8 trl) external returns (uint256 projectId) {
        if (trl < 1 || trl > 9) revert InvalidTRL(trl);
        if (bytes(metadataCID).length == 0) revert EmptyCID();
        projectId = ++projectCount;
        _projects[projectId] = Project({
            researcher: msg.sender,
            metadataCID: metadataCID,
            privateDetailHash: bytes32(0),
            trl: trl,
            status: Status.Draft,
            createdAt: uint64(block.timestamp)
        });
        emit ProjectRegistered(projectId, msg.sender, metadataCID, trl);
    }

    /// @notice Metadata is frozen once a raise opens, so funders see what they funded.
    function updateMetadata(uint256 projectId, string calldata metadataCID) external onlyResearcher(projectId) {
        if (_projects[projectId].status != Status.Draft) revert NotDraft(projectId);
        if (bytes(metadataCID).length == 0) revert EmptyCID();
        _projects[projectId].metadataCID = metadataCID;
        emit MetadataUpdated(projectId, metadataCID);
    }

    /// @notice Links a vault existence proof (keccak256 of ciphertext) to the project.
    function setPrivateDetailHash(uint256 projectId, bytes32 privateDetailHash) external onlyResearcher(projectId) {
        _projects[projectId].privateDetailHash = privateDetailHash;
        emit PrivateDetailHashSet(projectId, privateDetailHash);
    }

    function updateTRL(uint256 projectId, uint8 newTRL) external onlyRole(ATTESTOR_ROLE) {
        _requireExists(projectId);
        if (newTRL < 1 || newTRL > 9) revert InvalidTRL(newTRL);
        uint8 old = _projects[projectId].trl;
        _projects[projectId].trl = newTRL;
        emit TRLUpdated(projectId, old, newTRL, msg.sender);
    }

    function setStatus(uint256 projectId, Status status) external onlyRole(MODULE_ROLE) {
        _requireExists(projectId);
        _projects[projectId].status = status;
        emit StatusChanged(projectId, status);
    }

    function getProject(uint256 projectId) external view returns (Project memory) {
        _requireExists(projectId);
        return _projects[projectId];
    }

    function researcherOf(uint256 projectId) external view returns (address) {
        _requireExists(projectId);
        return _projects[projectId].researcher;
    }

    function statusOf(uint256 projectId) external view returns (Status) {
        _requireExists(projectId);
        return _projects[projectId].status;
    }

    function _requireExists(uint256 projectId) internal view {
        if (_projects[projectId].researcher == address(0)) revert UnknownProject(projectId);
    }
}
