#include "urma_failure_790.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure790> g_urma("urma_790");

bool UrmaFailure790::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_free_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty still actived, please deactived first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure790::GetName() const
{
    return "urma_free_jetty 执行释放 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure790::GetRootCauseDesc() const
{
    return "urma_free_jetty 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure790::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure790::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure790::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jetty still actived, please deactived first";
}

std::string UrmaFailure790::GetId() const
{
    return "urma_790";
}

} // namespace diag
