#include "urma_failure_058.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure058> g_urma("urma_058");

bool UrmaFailure058::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_add_jfr_p_vjetty_id_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add p_vjfr_id[' | grep -F ']: ret:' | grep -F ', p_jfr_id:' | grep -F ', v_jfr_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure058::GetName() const
{
    return "执行虚拟 JFR过程中依赖步骤失败";
}

std::string UrmaFailure058::GetRootCauseDesc() const
{
    return "函数用于执行虚拟 "
           "JFR，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure058::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure058::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure058::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_add_jfr_p_vjetty_id_info，Failed to add p_vjfr_id[，]: ret:，, "
           "p_jfr_id:，, v_jfr_id:";
}

std::string UrmaFailure058::GetId() const
{
    return "urma_058";
}

} // namespace diag
