#include "urma_failure_420.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure420> g_urma("urma_420");

bool UrmaFailure420::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_delete_pcontext' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get topo info, change to general mode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure420::GetName() const
{
    return "获取健康检查过程中依赖步骤失败";
}

std::string UrmaFailure420::GetRootCauseDesc() const
{
    return "函数用于获取健康检查，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure420::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure420::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure420::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_delete_pcontext，Failed to get topo info, change to general mode";
}

std::string UrmaFailure420::GetId() const
{
    return "urma_420";
}

} // namespace diag
