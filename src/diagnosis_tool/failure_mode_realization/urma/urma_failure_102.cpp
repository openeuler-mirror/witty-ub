#include "urma_failure_102.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure102> g_urma("urma_102");

bool UrmaFailure102::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_deactive_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Jfc state is wrong in deactive_jfc')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure102::GetName() const
{
    return "urma_deactive_jfc 执行激活 JFC 失败导致当前资源状态无法推进";
}

std::string UrmaFailure102::GetRootCauseDesc() const
{
    return "urma_deactive_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure102::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure102::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure102::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Jfc state is wrong in deactive_jfc";
}

std::string UrmaFailure102::GetId() const
{
    return "urma_102";
}

} // namespace diag
