#include "urma_failure_051.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure051> g_urma("urma_051");

bool UrmaFailure051::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_add_jfs_p_vjetty_id_info' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to add p_vjfs_id[' | grep -F ']: ret:' | grep -F ', p_jfs_id:' | grep -F ', v_jfs_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure051::GetName() const
{
    return "执行虚拟 JFS过程中依赖步骤失败";
}

std::string UrmaFailure051::GetRootCauseDesc() const
{
    return "函数用于执行虚拟 "
           "JFS，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作失败。";
}

RootCause UrmaFailure051::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure051::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure051::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_add_jfs_p_vjetty_id_info，Failed to add p_vjfs_id[，]: ret:，, "
           "p_jfs_id:，, v_jfs_id:";
}

std::string UrmaFailure051::GetId() const
{
    return "urma_051";
}

} // namespace diag
