#include "urma_0316_bondp_create_vseg_fail_register_vseg_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0316BondpCreateVsegFailRegisterVsegRet> g_urma("urma_0316");

bool Urma0316BondpCreateVsegFailRegisterVsegRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to register vseg, ret:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0316BondpCreateVsegFailRegisterVsegRet::GetName() const
{
    return "bondp_create_vseg Fail to register vseg, ret:%.";
}

std::string Urma0316BondpCreateVsegFailRegisterVsegRet::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0316BondpCreateVsegFailRegisterVsegRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0316BondpCreateVsegFailRegisterVsegRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0316BondpCreateVsegFailRegisterVsegRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to register vseg, ret:%.";
}

std::string Urma0316BondpCreateVsegFailRegisterVsegRet::GetId() const
{
    return "urma_0316";
}
} // namespace diag
