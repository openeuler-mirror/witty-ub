#include "urma_failure_453.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure453> g_urma("urma_453");

bool UrmaFailure453::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_notifier' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc notifier')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure453::GetName() const
{
    return "urma_create_notifier 分配 URMA 对象 临时参数失败导致创建流程无法继续";
}

std::string UrmaFailure453::GetRootCauseDesc() const
{
    return "urma_create_notifier 需要为 URMA 对象 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure453::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure453::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure453::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc notifier";
}

std::string UrmaFailure453::GetId() const
{
    return "urma_453";
}

} // namespace diag
