#include "urma_0926_get_topo_info_from_ko_failed_create_topo_map.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0926GetTopoInfoFromKoFailedCreateTopoMap> g_urma("urma_0926");

bool Urma0926GetTopoInfoFromKoFailedCreateTopoMap::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create topo map"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0926GetTopoInfoFromKoFailedCreateTopoMap::GetName() const
{
    return "get_topo_info_from_ko Failed to create topo map";
}

std::string Urma0926GetTopoInfoFromKoFailedCreateTopoMap::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0926GetTopoInfoFromKoFailedCreateTopoMap::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0926GetTopoInfoFromKoFailedCreateTopoMap::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0926GetTopoInfoFromKoFailedCreateTopoMap::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create topo map";
}

std::string Urma0926GetTopoInfoFromKoFailedCreateTopoMap::GetId() const
{
    return "urma_0926";
}
} // namespace diag
