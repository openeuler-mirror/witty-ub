#include "urma_1147_urma_delete_notifier_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1147UrmaDeleteNotifierResourceDeleteFailure> g_urma("urma_1147");

bool Urma1147UrmaDeleteNotifierResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete notifier, ret: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1147UrmaDeleteNotifierResourceDeleteFailure::GetName() const
{
    return "urma_delete_notifier 删除资源失败";
}

std::string Urma1147UrmaDeleteNotifierResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma1147UrmaDeleteNotifierResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1147UrmaDeleteNotifierResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1147UrmaDeleteNotifierResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete notifier, ret: %";
}

std::string Urma1147UrmaDeleteNotifierResourceDeleteFailure::GetId() const
{
    return "urma_1147";
}
} // namespace diag
