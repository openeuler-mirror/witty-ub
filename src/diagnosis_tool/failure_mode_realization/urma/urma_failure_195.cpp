#include "urma_failure_195.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure195> g_urma("urma_195");

bool UrmaFailure195::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_create_jetty' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'In matrix server, multi-device mode don'\''t support single path currently')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure195::GetName() const
{
    return "bondp_create_jetty 执行创建 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure195::GetRootCauseDesc() const
{
    return "bondp_create_jetty 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure195::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure195::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure195::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：In matrix server, multi-device mode don't support single path currently";
}

std::string UrmaFailure195::GetId() const
{
    return "urma_195";
}

} // namespace diag
