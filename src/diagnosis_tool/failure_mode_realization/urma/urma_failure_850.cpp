#include "urma_failure_850.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure850> g_urma("urma_850");

bool UrmaFailure850::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'restore_cr_local_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get vjetty.id of local_id:' | "
        "grep -F ', ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure850::GetName() const
{
    return "restore_cr_local_id 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure850::GetRootCauseDesc() const
{
    return "restore_cr_local_id 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure850::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure850::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure850::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get vjetty.id of local_id: , ret";
}

std::string UrmaFailure850::GetId() const
{
    return "urma_850";
}

} // namespace diag
