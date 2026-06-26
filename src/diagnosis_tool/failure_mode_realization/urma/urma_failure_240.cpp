#include "urma_failure_240.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure240> g_urma("urma_240");

bool UrmaFailure240::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("get_bonding_eid_by_target_eid") != std::string::npos &&
           message.find("Invalid param") != std::string::npos;
}

std::string UrmaFailure240::GetName() const
{
    return "bonding、EID、target状态不满足要求导致获取bonding、EID、target失败";
}

std::string UrmaFailure240::GetRootCauseDesc() const
{
    return "get_bonding_eid_by_target_"
           "eid执行获取bonding、EID、target时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure240::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure240::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure240::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_bonding_eid_by_target_eid，Invalid param。";
}

std::string UrmaFailure240::GetId() const
{
    return "urma_240";
}
} // namespace diag
