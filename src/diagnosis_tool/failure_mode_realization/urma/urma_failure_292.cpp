#include "urma_failure_292.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure292> g_urma("urma_292");

bool UrmaFailure292::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_perf_info") != std::string::npos &&
           message.find("Urma perf get info failed, need") != std::string::npos &&
           message.find("bytes buffer, but only") != std::string::npos && message.find("provided") != std::string::npos;
}

std::string UrmaFailure292::GetName() const
{
    return "下层查询返回失败导致获取PERF、INFO失败";
}

std::string UrmaFailure292::GetRootCauseDesc() const
{
    return "urma_get_perf_"
           "info需要从provider、驱动或缓存中获取PERF、INFO状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure292::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure292::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure292::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_perf_info，Urma perf get info failed, need，bytes buffer, but "
           "only，pro"
           "vided。";
}

std::string UrmaFailure292::GetId() const
{
    return "urma_292";
}
} // namespace diag
