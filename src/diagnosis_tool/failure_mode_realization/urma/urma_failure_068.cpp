#include "urma_failure_068.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure068> g_urma("urma_068");

bool UrmaFailure068::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_add_jetty_p_vjetty_id_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add p_vjetty_id[' | grep -F ']: ret:' | grep -F ', p_jetty_id:' | grep -F ', v_jetty_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure068::GetName() const
{
    return "执行虚拟 Jetty过程中依赖步骤失败";
}

std::string UrmaFailure068::GetRootCauseDesc() const
{
    return "函数用于执行虚拟 "
           "Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure068::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure068::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure068::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_add_jetty_p_vjetty_id_info，Failed to add p_vjetty_id[，]: "
           "ret:，, p_jetty_id:，, v_jetty_id:。";
}

std::string UrmaFailure068::GetId() const
{
    return "urma_068";
}

} // namespace diag
