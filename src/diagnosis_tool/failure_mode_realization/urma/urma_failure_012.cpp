#include "urma_failure_012.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure012> g_urma("urma_012");

bool UrmaFailure012::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init active indices'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure012::GetName() const
{
    return "初始化物理 Jetty过程中依赖步骤失败";
}

std::string UrmaFailure012::GetRootCauseDesc() const
{
    return "函数用于初始化物理 "
           "Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure012::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure012::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure012::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pjetty，Failed to init active indices";
}

std::string UrmaFailure012::GetId() const
{
    return "urma_012";
}

} // namespace diag
