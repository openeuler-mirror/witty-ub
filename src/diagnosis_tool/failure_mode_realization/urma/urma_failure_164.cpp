#include "urma_failure_164.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure164> g_urma("urma_164");

bool UrmaFailure164::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_set_bonding_mode") != std::string::npos &&
           message.find("Failed to create pctx when set bonding mode, ret:") != std::string::npos;
}

std::string UrmaFailure164::GetName() const
{
    return "下层资源创建失败导致设置bonding、MODE失败";
}

std::string UrmaFailure164::GetRootCauseDesc() const
{
    return "bondp_set_bonding_"
           "mode在设置bonding、MODE过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure164::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure164::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure164::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Failed to create pctx when set bonding mode, "
           "ret:。";
}

std::string UrmaFailure164::GetId() const
{
    return "urma_164";
}
} // namespace diag
