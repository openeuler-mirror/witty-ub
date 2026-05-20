#include "urma_failure_794.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure794> g_urma("urma_794");

bool UrmaFailure794::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty still deactived, can not delete'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure794::GetName() const
{
    return "urma_delete_jetty 执行删除 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure794::GetRootCauseDesc() const
{
    return "urma_delete_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure794::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure794::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure794::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty still deactived, can not delete";
}

std::string UrmaFailure794::GetId() const
{
    return "urma_794";
}

} // namespace diag
