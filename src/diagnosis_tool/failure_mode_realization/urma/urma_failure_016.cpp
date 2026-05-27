#include "urma_failure_016.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure016> g_urma("urma_016");

bool UrmaFailure016::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bdp_v_conn_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init slide window in bdp_v_conn_table_add'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure016::GetName() const
{
    return "初始化URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure016::GetRootCauseDesc() const
{
    return "函数用于初始化URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次U"
           "RMA操作失败。";
}

RootCause UrmaFailure016::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure016::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure016::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bdp_v_conn_init，Failed to init slide window in bdp_v_conn_table_add";
}

std::string UrmaFailure016::GetId() const
{
    return "urma_016";
}

} // namespace diag
