#include "urma_failure_473.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure473> g_urma("urma_473");

bool UrmaFailure473::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_net_addr_list' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to get netaddr list, ret:' | grep -F ', max_netaddr_cnt:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure473::GetName() const
{
    return "urma_get_net_addr_list 执行获取 URMA 对象 失败导致当前资源状态无法推进";
}

std::string UrmaFailure473::GetRootCauseDesc() const
{
    return "urma_get_net_addr_list 调用下层 provider、bond 组件或系统接口处理 URMA 对象 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure473::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure473::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure473::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get netaddr list, ret: , max_netaddr_cnt";
}

std::string UrmaFailure473::GetId() const
{
    return "urma_473";
}

} // namespace diag
