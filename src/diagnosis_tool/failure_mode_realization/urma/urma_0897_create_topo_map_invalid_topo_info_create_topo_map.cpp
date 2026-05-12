#include "urma_0897_create_topo_map_invalid_topo_info_create_topo_map.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap> g_urma("urma_0897");

bool Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid topo info to create topo map"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::GetName() const
{
    return "create_topo_map Invalid topo info to create topo map";
}

std::string Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid topo info to create topo map";
}

std::string Urma0897CreateTopoMapInvalidTopoInfoCreateTopoMap::GetId() const
{
    return "urma_0897";
}
} // namespace diag
