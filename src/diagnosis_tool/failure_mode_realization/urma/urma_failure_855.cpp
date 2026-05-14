#include "urma_failure_855.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure855> g_urma("urma_855");

bool UrmaFailure855::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_queue_pop_tail' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'data is NULL')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure855::GetName() const
{
    return "bdp_queue_pop_tail 执行处理 URMA 对象 失败导致当前资源状态无法推进";
}

std::string UrmaFailure855::GetRootCauseDesc() const
{
    return "bdp_queue_pop_tail 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure855::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure855::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure855::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：data is NULL";
}

std::string UrmaFailure855::GetId() const
{
    return "urma_855";
}

} // namespace diag
