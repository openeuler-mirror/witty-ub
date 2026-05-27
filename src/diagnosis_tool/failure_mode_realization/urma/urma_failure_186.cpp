#include "urma_failure_186.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure186> g_urma("urma_186");

bool UrmaFailure186::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_dev_cap' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty cfg out of range, jfs_depth:' | grep -F ', max_jfs_depth:' | grep -F ', inline_data:' | "
        "grep -F ', max_jfs_inline_len:' | grep -F ', jfr_depth:' | grep -F ', max_jfr_depth:' | grep -F ', jfs_sge:' "
        "| "
        "grep -F 'hu, max_jfs_sge:' | grep -F ', jfs_rsge:' | grep -F 'hu, max_jfs_rsge:' | grep -F ', jfr_sge:' | "
        "grep -F 'hu, max_jfr_sge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure186::GetName() const
{
    return "创建Jetty过程中依赖步骤失败";
}

std::string UrmaFailure186::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure186::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure186::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure186::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_create_jetty_check_dev_cap，jetty cfg out of range, jfs_depth:，, "
           "max_jfs_depth:，, inline_data:，, max_jfs_inline_len:，, jfr_depth:，, max_jfr_depth:，, jfs_sge:，hu, "
           "max_jfs_sge:，, jfs_rsge:，hu, max_jfs_rsge:，, jfr_sge:，hu, max_jfr_sge:";
}

std::string UrmaFailure186::GetId() const
{
    return "urma_186";
}

} // namespace diag
