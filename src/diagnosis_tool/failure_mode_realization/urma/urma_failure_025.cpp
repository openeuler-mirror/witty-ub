#include "urma_failure_025.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure025> g_urma("urma_025");

bool UrmaFailure025::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_global_ctx_init' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc global context')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure025::GetName() const
{
    return "bondp_global_ctx_init 分配 context 临时参数失败导致初始化流程无法继续";
}

std::string UrmaFailure025::GetRootCauseDesc() const
{
    return "bondp_global_ctx_init 需要为 context 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure025::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure025::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure025::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc global context";
}

std::string UrmaFailure025::GetId() const
{
    return "urma_025";
}

} // namespace diag
