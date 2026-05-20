#include "urma_failure_787.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure787> g_urma("urma_787");

bool UrmaFailure787::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_delete_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]Failed to delete jfce, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure787::GetName() const
{
    return "urma_delete_jfce 执行删除 JFCE 失败导致当前资源状态无法推进";
}

std::string UrmaFailure787::GetRootCauseDesc() const
{
    return "urma_delete_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure787::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure787::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure787::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]Failed to delete jfce, ret";
}

std::string UrmaFailure787::GetId() const
{
    return "urma_787";
}

} // namespace diag
