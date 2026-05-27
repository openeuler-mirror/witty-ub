#include "urma_failure_006.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure006> g_urma("urma_006");

bool UrmaFailure006::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bondp init jfr fail:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure006::GetName() const
{
    return "初始化JFR过程中依赖步骤失败";
}

std::string UrmaFailure006::GetRootCauseDesc() const
{
    return "函数用于初始化JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure006::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure006::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure006::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vjfr，bondp init jfr fail:";
}

std::string UrmaFailure006::GetId() const
{
    return "urma_006";
}

} // namespace diag
