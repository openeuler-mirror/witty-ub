#include "urma_failure_029.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure029> g_urma("urma_029");

bool UrmaFailure029::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pcontext' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init port info list'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure029::GetName() const
{
    return "初始化端口过程中依赖步骤失败";
}

std::string UrmaFailure029::GetRootCauseDesc() const
{
    return "函数用于初始化端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA"
           "操作失败。";
}

RootCause UrmaFailure029::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure029::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure029::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_pcontext，Failed to init port info list";
}

std::string UrmaFailure029::GetId() const
{
    return "urma_029";
}

} // namespace diag
