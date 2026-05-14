#include "urma_failure_279.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure279> g_urma("urma_279");

bool UrmaFailure279::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_queue_push_tail' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc bdp_queue_node')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure279::GetName() const
{
    return "bdp_queue_push_tail 分配 URMA 对象 临时参数失败导致处理流程无法继续";
}

std::string UrmaFailure279::GetRootCauseDesc() const
{
    return "bdp_queue_push_tail 需要为 URMA 对象 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure279::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure279::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure279::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc bdp_queue_node";
}

std::string UrmaFailure279::GetId() const
{
    return "urma_279";
}

} // namespace diag
