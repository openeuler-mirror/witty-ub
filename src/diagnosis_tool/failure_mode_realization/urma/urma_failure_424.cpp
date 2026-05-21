#include "urma_failure_424.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure424> g_urma("urma_424");

bool UrmaFailure424::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_create_jetty_check_dev_cap' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty cfg out of range, jfs_depth:' | "
        "grep -F ', max_jfs_depth:' | "
        "grep -F ', inline_data:' | "
        "grep -F ', max_jfs_inline_len:' | "
        "grep -F ', jfr_depth:' | "
        "grep -F ', max_jfr_depth:' | "
        "grep -F ', jfs_sge:' | "
        "grep -F ', max_jfs_sge:' | "
        "grep -F ', jfs_rsge:' | "
        "grep -F ', max_jfs_rsge:' | "
        "grep -F ', jfr_sge:' | "
        "grep -F ', max_jfr_sge:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure424::GetName() const
{
    return "urma_create_jetty_check_dev_cap 执行创建 设备 失败导致当前资源状态无法推进";
}

std::string UrmaFailure424::GetRootCauseDesc() const
{
    return "urma_create_jetty_check_dev_cap 调用下层 provider、bond 组件或系统接口处理 设备 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure424::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure424::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure424::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty cfg out of range, jfs_depth:, max_jfs_depth: , inline_data:, "
           "max_jfs_inline_len: , jfr_depth:, max_jfr_depth: , jf";
}

std::string UrmaFailure424::GetId() const
{
    return "urma_424";
}

} // namespace diag
