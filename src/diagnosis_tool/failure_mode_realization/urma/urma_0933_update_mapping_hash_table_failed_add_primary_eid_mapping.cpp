#include "urma_0933_update_mapping_hash_table_failed_add_primary_eid_mapping.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping> g_urma("urma_0933");

bool Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add primary eid to mapping hash table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::GetName() const
{
    return "update_mapping_hash_table Failed to add primary eid to mapping";
}

std::string Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `eid_mapping_hash_table_add(&topo_map->eid_mapping_hash_table, (urma_eid_t "
           "*)ue_info->primary_eid, (u`；该路径返回 -1";
}

RootCause Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add primary eid to mapping hash table";
}

std::string Urma0933UpdateMappingHashTableFailedAddPrimaryEidMapping::GetId() const
{
    return "urma_0933";
}
} // namespace diag
