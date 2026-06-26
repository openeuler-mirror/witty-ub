#include "urma_failure_399.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure399> g_urma("urma_399");

bool UrmaFailure399::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("schedule_send_balance") != std::string::npos &&
           message.find("Unsupported bonding level:") != std::string::npos;
}

std::string UrmaFailure399::GetName() const
{
    return "provider未提供schedule_send_balance操作实现导致发送schedule、balance失败";
}

std::string UrmaFailure399::GetRootCauseDesc() const
{
    return "schedule_send_"
           "balance需要通过provider操作表完成发送schedule、balance，当前设备provider缺少对应回调或能力不支持该操作。";
}

RootCause UrmaFailure399::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure399::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure399::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_send_balance，Unsupported bonding level:。";
}

std::string UrmaFailure399::GetId() const
{
    return "urma_399";
}
} // namespace diag
