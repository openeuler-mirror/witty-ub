#include "urma_failure_401.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure401> g_urma("urma_401");

bool UrmaFailure401::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr cfg out of range, depth:' | grep -F ', max_depth:' | grep -F ', sge:' | grep -F ', max_sge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure401::GetName() const
{
    return "分配JFR过程中依赖步骤失败";
}

std::string UrmaFailure401::GetRootCauseDesc() const
{
    return "函数用于分配JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure401::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure401::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure401::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfr，jfr cfg out of range, depth:，, max_depth:，, sge:，, max_sge:";
}

std::string UrmaFailure401::GetId() const
{
    return "urma_401";
}

} // namespace diag
