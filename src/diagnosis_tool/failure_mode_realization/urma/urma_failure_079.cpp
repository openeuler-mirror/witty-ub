#include "urma_failure_079.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure079> g_urma("urma_079");

bool UrmaFailure079::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_modify_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'modify pjetty fail, index:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure079::GetName() const
{
    return "修改物理 Jetty过程中依赖步骤失败";
}

std::string UrmaFailure079::GetRootCauseDesc() const
{
    return "函数用于修改物理 "
           "Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure079::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure079::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure079::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_modify_jetty，modify pjetty fail, index:，, ret:";
}

std::string UrmaFailure079::GetId() const
{
    return "urma_079";
}

} // namespace diag
