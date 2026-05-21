#include "urma_failure_113.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure113> g_urma("urma_113");

bool UrmaFailure113::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec ops->deactive_jfs'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure113::GetName() const
{
    return "urma_deactive_jfs 执行激活 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure113::GetRootCauseDesc() const
{
    return "urma_deactive_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure113::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure113::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure113::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to exec ops->deactive_jfs";
}

std::string UrmaFailure113::GetId() const
{
    return "urma_113";
}

} // namespace diag
