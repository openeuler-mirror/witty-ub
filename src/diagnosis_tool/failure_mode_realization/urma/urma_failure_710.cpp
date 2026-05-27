#include "urma_failure_710.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure710> g_urma("urma_710");

bool UrmaFailure710::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_modify_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'modify pjfc fail, index:' | grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure710::GetName() const
{
    return "修改物理 JFC过程中依赖步骤失败";
}

std::string UrmaFailure710::GetRootCauseDesc() const
{
    return "函数用于修改物理 "
           "JFC，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure710::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure710::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure710::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_modify_jfc，modify pjfc fail, index:，, ret:";
}

std::string UrmaFailure710::GetId() const
{
    return "urma_710";
}

} // namespace diag
