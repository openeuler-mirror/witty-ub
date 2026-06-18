#include "urma_failure_291.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure291> g_urma("urma_291");

bool UrmaFailure291::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_perf_info") != std::string::npos &&
           message.find("Urma perf info get failed, perf_buf or length is invalid") != std::string::npos;
}

std::string UrmaFailure291::GetName() const
{
    return "下层查询返回失败导致获取PERF、INFO失败";
}

std::string UrmaFailure291::GetRootCauseDesc() const
{
    return "urma_get_perf_"
           "info需要从provider、驱动或缓存中获取PERF、INFO状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure291::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure291::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure291::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_perf_info，Urma perf info get failed, perf_buf or length is "
           "invalid。";
}

std::string UrmaFailure291::GetId() const
{
    return "urma_291";
}
} // namespace diag
