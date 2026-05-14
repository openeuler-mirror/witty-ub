#include "urma_failure_179.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure179> g_urma("urma_179");

bool UrmaFailure179::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_create_jfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'In matrix server, JFS don'\''t support single-path mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure179::GetName() const
{
    return "bondp_create_jfs 执行创建 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure179::GetRootCauseDesc() const
{
    return "bondp_create_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure179::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure179::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure179::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：In matrix server, JFS don't support single-path mode";
}

std::string UrmaFailure179::GetId() const
{
    return "urma_179";
}

} // namespace diag
