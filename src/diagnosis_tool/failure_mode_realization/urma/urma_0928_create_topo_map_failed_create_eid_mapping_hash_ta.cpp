#include "urma_0928_create_topo_map_failed_create_eid_mapping_hash_ta.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0928CreateTopoMapFailedCreateEidMappingHashTa> g_urma("urma_0928");

bool Urma0928CreateTopoMapFailedCreateEidMappingHashTa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create eid_mapping_hash_table"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0928CreateTopoMapFailedCreateEidMappingHashTa::GetName() const
{
    return "create_topo_map Failed to create eid_mapping_hash_ta";
}

std::string Urma0928CreateTopoMapFailedCreateEidMappingHashTa::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0928CreateTopoMapFailedCreateEidMappingHashTa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0928CreateTopoMapFailedCreateEidMappingHashTa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0928CreateTopoMapFailedCreateEidMappingHashTa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create eid_mapping_hash_table";
}

std::string Urma0928CreateTopoMapFailedCreateEidMappingHashTa::GetId() const
{
    return "urma_0928";
}
} // namespace diag
