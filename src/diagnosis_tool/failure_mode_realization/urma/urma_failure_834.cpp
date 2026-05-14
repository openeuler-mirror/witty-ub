#include "urma_failure_834.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure834> g_urma("urma_834");

bool UrmaFailure834::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_modify_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'modify pjfc fail, index:, ret')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure834::GetName() const
{
    return "bondp_modify_jfc 执行修改 JFC 失败导致当前资源状态无法推进";
}

std::string UrmaFailure834::GetRootCauseDesc() const
{
    return "bondp_modify_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure834::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure834::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure834::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：modify pjfc fail, index:, ret";
}

std::string UrmaFailure834::GetId() const
{
    return "urma_834";
}

} // namespace diag
