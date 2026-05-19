#include "urma_failure_693.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure693> g_urma("urma_693");

bool UrmaFailure693::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_delete_jfce' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to delete jfce[' | grep -F '], still in use. use_cnt:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure693::GetName() const
{
    return "bondp_delete_jfce 执行删除 JFCE 失败导致当前资源状态无法推进";
}

std::string UrmaFailure693::GetRootCauseDesc() const
{
    return "bondp_delete_jfce 调用下层 provider、bond 组件或系统接口处理 JFCE 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure693::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure693::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure693::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete jfce[], still in use. use_cnt";
}

std::string UrmaFailure693::GetId() const
{
    return "urma_693";
}

} // namespace diag
