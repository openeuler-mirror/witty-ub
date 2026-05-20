#include "urma_failure_499.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure499> g_urma("urma_499");

bool UrmaFailure499::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'get_dev_and_ctx_by_name' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get eid_idx'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure499::GetName() const
{
    return "get_dev_and_ctx_by_name 执行获取 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure499::GetRootCauseDesc() const
{
    return "get_dev_and_ctx_by_name 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure499::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure499::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure499::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get eid_idx";
}

std::string UrmaFailure499::GetId() const
{
    return "urma_499";
}

} // namespace diag
