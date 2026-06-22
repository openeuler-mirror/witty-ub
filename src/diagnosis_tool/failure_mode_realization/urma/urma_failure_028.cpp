#include "urma_failure_028.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure028> g_urma("urma_028");

bool UrmaFailure028::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_init_member_eid_info_list") != std::string::npos &&
           message.find("Invalid slave device number") != std::string::npos &&
           message.find("of device") != std::string::npos;
}

std::string UrmaFailure028::GetName() const
{
    return "member、EID、INFO状态不满足要求导致初始化member、EID、INFO失败";
}

std::string UrmaFailure028::GetRootCauseDesc() const
{
    return "bondp_init_member_eid_info_"
           "list执行初始化member、EID、INFO时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure028::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure028::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure028::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init_member_eid_info_list，Invalid slave device number，of "
           "device。";
}

std::string UrmaFailure028::GetId() const
{
    return "urma_028";
}
} // namespace diag
