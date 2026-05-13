#include "urma_0934_update_mapping_hash_table_failed_add_port_eid_mapping_ha.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa> g_urma("urma_0934");

bool Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add port eid to mapping hash table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::GetName() const
{
    return "update_mapping_hash_table Failed to add port eid to mapping ha";
}

std::string Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `eid_mapping_hash_table_add(&topo_map->eid_mapping_hash_table, (urma_eid_t "
           "*)ue_info->port_eid[port_i`；该路径返回 -1";
}

RootCause Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add port eid to mapping hash table";
}

std::string Urma0934UpdateMappingHashTableFailedAddPortEidMappingHa::GetId() const
{
    return "urma_0934";
}
} // namespace diag
