#include "urma_0932_update_mapping_hash_table_failed_add_agg_eid_mapping_has.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas> g_urma("urma_0932");

bool Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to add agg eid to mapping hash table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::GetName() const
{
    return "update_mapping_hash_table Failed to add agg eid to mapping has";
}

std::string Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `eid_mapping_hash_table_add(&topo_map->eid_mapping_hash_table, (urma_eid_t "
           "*)cur_dev->agg_eid, (urma_`；该路径返回 -1";
}

RootCause Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to add agg eid to mapping hash table";
}

std::string Urma0932UpdateMappingHashTableFailedAddAggEidMappingHas::GetId() const
{
    return "urma_0932";
}
} // namespace diag
