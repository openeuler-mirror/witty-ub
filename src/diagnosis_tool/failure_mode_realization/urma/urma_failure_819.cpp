#include "urma_failure_819.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure819> g_urma("urma_819");

bool UrmaFailure819::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jfr cfg out of range, depth:' | grep -F ', max_depth:' | grep -F ', sge:' | grep -F ', max_sge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure819::GetName() const
{
    return "激活JFR过程中依赖步骤失败";
}

std::string UrmaFailure819::GetRootCauseDesc() const
{
    return "函数用于激活JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure819::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure819::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure819::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfr，jfr cfg out of range, depth:，, max_depth:，, sge:，, max_sge:";
}

std::string UrmaFailure819::GetId() const
{
    return "urma_819";
}

} // namespace diag
