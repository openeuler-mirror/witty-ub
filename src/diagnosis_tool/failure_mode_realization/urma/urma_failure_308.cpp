#include "urma_failure_308.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure308> g_urma("urma_308");

bool UrmaFailure308::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_alloc_token_id' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'ioctl failed in urma_cmd_alloc_token_id, ret:, errno')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure308::GetName() const
{
    return "urma_cmd_alloc_token_id 分配 token_id 临时参数失败导致分配流程无法继续";
}

std::string UrmaFailure308::GetRootCauseDesc() const
{
    return "urma_cmd_alloc_token_id 需要为 token_id 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 "
           "provider 调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure308::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure308::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure308::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ioctl failed in urma_cmd_alloc_token_id, ret:, errno";
}

std::string UrmaFailure308::GetId() const
{
    return "urma_308";
}

} // namespace diag
