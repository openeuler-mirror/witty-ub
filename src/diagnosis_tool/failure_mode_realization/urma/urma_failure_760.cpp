#include "urma_failure_760.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure760> g_urma("urma_760");

bool UrmaFailure760::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfc is deactived, can not delete')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure760::GetName() const
{
    return "urma_delete_jfc 执行删除 JFC 失败导致当前资源状态无法推进";
}

std::string UrmaFailure760::GetRootCauseDesc() const
{
    return "urma_delete_jfc 调用下层 provider、bond 组件或系统接口处理 JFC 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure760::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure760::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure760::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfc is deactived, can not delete";
}

std::string UrmaFailure760::GetId() const
{
    return "urma_760";
}

} // namespace diag
