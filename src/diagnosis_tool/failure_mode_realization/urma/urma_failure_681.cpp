#include "urma_failure_681.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure681> g_urma("urma_681");

bool UrmaFailure681::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_set_bonding_mode") != std::string::npos &&
           message.find("Unsupported bonding level:") != std::string::npos;
}

std::string UrmaFailure681::GetName() const
{
    return "provider未提供bondp_set_bonding_mode操作实现导致设置bonding、MODE失败";
}

std::string UrmaFailure681::GetRootCauseDesc() const
{
    return "bondp_set_bonding_"
           "mode需要通过provider操作表完成设置bonding、MODE，当前设备provider缺少对应回调或能力不支持该操作。";
}

RootCause UrmaFailure681::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure681::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure681::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Unsupported bonding level:。";
}

std::string UrmaFailure681::GetId() const
{
    return "urma_681";
}
} // namespace diag
