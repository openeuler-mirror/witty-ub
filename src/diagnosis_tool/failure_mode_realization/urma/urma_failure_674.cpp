#include "urma_failure_674.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure674> g_urma("urma_674");

bool UrmaFailure674::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_user_ctl") != std::string::npos &&
           message.find("Unsupported opcode, opcode:") != std::string::npos;
}

std::string UrmaFailure674::GetName() const
{
    return "provider未提供bondp_user_ctl操作实现导致userUSER、CTL失败";
}

std::string UrmaFailure674::GetRootCauseDesc() const
{
    return "bondp_user_ctl需要通过provider操作表完成userUSER、CTL，当前设备provider缺少对应回调或能力不支持该操作。";
}

RootCause UrmaFailure674::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure674::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure674::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl，Unsupported opcode, opcode:。";
}

std::string UrmaFailure674::GetId() const
{
    return "urma_674";
}
} // namespace diag
