#include "urma_failure_027.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure027> g_urma("urma_027");

bool UrmaFailure027::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_init_member_eid_info_list") != std::string::npos &&
           message.find("Failed to get slave device info") != std::string::npos;
}

std::string UrmaFailure027::GetName() const
{
    return "下层查询返回失败导致初始化member、EID、INFO失败";
}

std::string UrmaFailure027::GetRootCauseDesc() const
{
    return "bondp_init_member_eid_info_"
           "list需要从provider、驱动或缓存中获取member、EID、INFO状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure027::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure027::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure027::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_init_member_eid_info_list，Failed to get slave device info。";
}

std::string UrmaFailure027::GetId() const
{
    return "urma_027";
}
} // namespace diag
